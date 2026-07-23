import { of, throwError } from 'rxjs';

import { ApiService } from '../../services/api.service';
import { WifiSettingsComponent } from './wifi-settings.component';

describe('WifiSettingsComponent', () => {
    const operationStorageKey = 'brainWifiOperationId';
    let api: jasmine.SpyObj<ApiService>;
    let component: WifiSettingsComponent;

    beforeEach(() => {
        localStorage.removeItem(operationStorageKey);
        api = jasmine.createSpyObj<ApiService>('ApiService', [
            'getWifiList',
            'getWifiOperation',
            'addWifi',
            'removeWifi'
        ]);
        api.getWifiList.and.returnValue(of({
            success: true,
            networks: [{
                uuid: 'home-uuid',
                name: 'Home',
                active: true
            }]
        }));
        component = new WifiSettingsComponent(api);
    });

    afterEach(() => {
        component.ngOnDestroy();
        localStorage.removeItem(operationStorageKey);
    });

    it('clears a persisted operation that the restarted backend no longer knows', () => {
        localStorage.setItem(operationStorageKey, 'stale-operation');
        api.getWifiOperation.and.returnValue(throwError(() => ({
            status: 404,
            error: { error: 'Wi-Fi operation not found' }
        })));

        component.ngOnInit();

        expect(localStorage.getItem(operationStorageKey)).toBeNull();
        expect(component.isAdding).toBeFalse();
        expect(component.statusType).toBe('info');
        expect(component.statusMessage).toContain('current network state');
        expect(api.getWifiList).toHaveBeenCalledTimes(2);
    });
});
