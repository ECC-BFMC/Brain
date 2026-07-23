import { of, throwError } from 'rxjs';

import { ApiService } from '../../services/api.service';
import { WifiSettingsComponent } from './wifi-settings.component';

describe('WifiSettingsComponent', () => {
    let api: jasmine.SpyObj<ApiService>;
    let component: WifiSettingsComponent;

    beforeEach(() => {
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
    });

    it('loads live network state without resuming a browser-persisted operation', () => {
        localStorage.setItem('brainWifiOperationId', 'legacy-stale-operation');

        component.ngOnInit();

        expect(component.networks[0].name).toBe('Home');
        expect(component.isAdding).toBeFalse();
        expect(api.getWifiOperation).not.toHaveBeenCalled();

        localStorage.removeItem('brainWifiOperationId');
    });

    it('stops an in-memory operation that the restarted backend no longer knows', () => {
        api.getWifiOperation.and.returnValue(throwError(() => ({
            status: 404,
            error: { error: 'Wi-Fi operation not found' }
        })));

        (component as any).watchOperation('missing-operation');

        expect(component.isAdding).toBeFalse();
        expect(component.statusType).toBe('info');
        expect(component.statusMessage).toContain('current network state');
        expect(api.getWifiList).toHaveBeenCalledTimes(1);
    });
});
